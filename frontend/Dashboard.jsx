const { useState, useEffect, useRef } = React;

function Dashboard() {
  const [data, setData] = useState(null);
  const ppiChart = useRef(null);
  const cryptoChart = useRef(null);
  const [chat, setChat] = useState([]);


  useEffect(() => {
    fetch('/api/panorama')
      .then(r => r.json())
      .then(d => {
        setData(d);
        setChat(d.discord || []);
      })
      .catch(err => console.error(err));
  }, []);

  useEffect(() => {
    if (!data) return;
    if (ppiChart.current) {
      const ctx = ppiChart.current.getContext('2d');
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.macro.map(m => m.timestamp).reverse(),
          datasets: [{
            label: 'PPI',
            data: data.macro.map(m => m.value).reverse(),
            borderColor: 'blue',
            fill: false
          }]
        },
        options: { scales: { x: { display: false } } }
      });
    }
    if (cryptoChart.current) {
      const ctx = cryptoChart.current.getContext('2d');
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.crypto.map(c => c.symbol),
          datasets: [{
            label: 'Price',
            data: data.crypto.map(c => c.value),
            borderColor: 'green',
            fill: false
          }]
        }
      });
    }
  }, [data]);

  if (!data) return React.createElement('div', null, 'Loading...');

  return (
    React.createElement('div', { className: 'dashboard' },
      React.createElement('div', { className: 'panel' },
        React.createElement('h3', null, 'Political Signals'),
        React.createElement('ul', null,
          data.political.map((p, i) => React.createElement('li', { key: i }, `${p.symbol} ${p.metrics.Representative || ''}`))
        )
      ),
      React.createElement('div', { className: 'panel' },
        React.createElement('h3', null, 'News Feed'),
        React.createElement('ul', null,
          data.news.map((n, i) => React.createElement('li', { key: i },
            React.createElement('a', { href: n.metrics.url, target: '_blank' }, n.metrics.title)
          ))
        )
      ),
      React.createElement('div', { className: 'panel' },
        React.createElement('h3', null, 'Crypto Snapshot'),
        React.createElement('canvas', { ref: cryptoChart })
      ),
      React.createElement('div', { className: 'panel' },
        React.createElement('h3', null, 'PPI Trend'),
        React.createElement('canvas', { ref: ppiChart })
      ),
      React.createElement('div', { className: 'panel' },
        React.createElement('h3', null, 'Community Chat'),
        React.createElement('ul', null,
          chat.map(m => {
            const v = data.validated && data.validated[m.id];
            if (v && v.trustScore && v.trustScore <= 2) return null;
            return React.createElement('li', { key: m.id }, `${m.author}: ${m.content}`,
              v && v.trustScore ? ` (${v.trustScore}/5)` : ''
            );
          })
        )
      )
    )
  );
}

ReactDOM.render(React.createElement(Dashboard), document.getElementById('dashboard-root'));
