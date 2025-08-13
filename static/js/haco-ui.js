async function fetchHaco(){
    const symbol = document.getElementById('symbol').value.trim();
    const timeframe = document.getElementById('timeframe').value.trim();
    const lenUp = document.getElementById('lenUp').value;
    const lenDown = document.getElementById('lenDown').value;
    const alertLookback = document.getElementById('alertLookback').value;
    const lookback = document.getElementById('lookback').value;
    const url = `/api/signals/haco?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&lengthUp=${lenUp}&lengthDown=${lenDown}&alertLookback=${alertLookback}&lookback=${lookback}`;
    const res = await fetch(url);
    if(!res.ok){
        alert('No data');
        return;
    }
    const data = await res.json();
    renderChart(data.series);
    explainLast(data.last);
}

function renderChart(series){
    const chartEl = document.getElementById('chart');
    chartEl.innerHTML = '';
    const chart = LightweightCharts.createChart(chartEl, {height:400});
    const candleSeries = chart.addCandlestickSeries();
    const haToggle = document.getElementById('toggleHa').checked;

    const markers = [];
    const candles = series.map(bar => {
        const res = {time: bar.time, open: bar.o, high: bar.h, low: bar.l, close: bar.c};
        if(bar.state){
            res.color = '#2ecc71';
            res.borderColor = '#2ecc71';
        }else{
            res.color = '#e74c3c';
            res.borderColor = '#e74c3c';
        }
        if(bar.upw) markers.push({time: bar.time, position:'belowBar', color:'green', shape:'arrowUp'});
        if(bar.dnw) markers.push({time: bar.time, position:'aboveBar', color:'red', shape:'arrowDown'});
        return res;
    });
    candleSeries.setData(candles);
    candleSeries.setMarkers(markers);

    const zlHaU = chart.addLineSeries({color:'blue'});
    const zlClU = chart.addLineSeries({color:'orange'});
    const zlHaD = chart.addLineSeries({color:'purple'});
    const zlClD = chart.addLineSeries({color:'gray'});

    zlHaU.setData(series.map(b=>({time:b.time, value:b.ZlHaU})));
    zlClU.setData(series.map(b=>({time:b.time, value:b.ZlClU})));
    zlHaD.setData(series.map(b=>({time:b.time, value:b.ZlHaD})));
    zlClD.setData(series.map(b=>({time:b.time, value:b.ZlClD})));

    if(haToggle){
        const haSeries = chart.addCandlestickSeries({upColor:'#999', downColor:'#555'});
        haSeries.setData(series.map(b=>({time:b.time, open:b.haOpen, high:Math.max(b.h,b.haOpen), low:Math.min(b.l,b.haOpen), close:b.haC})));
    }
}

function explainLast(last){
    const el = document.getElementById('explain');
    el.innerHTML = `<p>State: ${last.state} (${last.upw?'UP':'')}${last.dnw?'DOWN':''}</p><p>${last.reasons}</p>`;
}

async function scan(direction){
    const list = document.getElementById('scanList').value.split(',').map(s=>s.trim().toUpperCase()).filter(Boolean);
    const timeframe = document.getElementById('timeframe').value.trim();
    const results = [];
    for(const sym of list){
        const url = `/api/signals/haco?symbol=${sym}&timeframe=${timeframe}&lookback=2`;
        try{
            const res = await fetch(url);
            if(!res.ok) continue;
            const data = await res.json();
            if(direction==='buy' && data.last.upw) results.push({sym, mark:'✅'});
            else if(direction==='sell' && data.last.dnw) results.push({sym, mark:'❌'});
            else results.push({sym, mark:data.last.state?'⤴':'⤵'});
        }catch(e){}
    }
    const out = results.map(r=>`${r.sym} ${r.mark}`).join('<br>');
    document.getElementById('scanResults').innerHTML = out;
}

document.getElementById('run').addEventListener('click', fetchHaco);
document.getElementById('scanBuy').addEventListener('click', ()=>scan('buy'));
document.getElementById('scanSell').addEventListener('click', ()=>scan('sell'));

fetchHaco();
