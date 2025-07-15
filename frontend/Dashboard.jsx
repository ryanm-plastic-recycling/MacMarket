const { useState, useEffect, useRef } = React;

function Dashboard() {
  const [data, setData] = useState(null);
  const ppiChart = useRef(null);
  const cryptoChart = useRef(null);
  const [chat, setChat] = useState([]);


  useEffect(() => {
    let mounted = true;
    fetch('/api/panorama')
      .then(r => r.json())
      .then(d => {
        if (!mounted) return;
        setData(d);
        setChat(d.discord || []);
      })
      .catch(err => console.error(err));
    return () => {
      mounted = false;
    };
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

  const politicalItems = [
    ...(data.political?.quiver || []),
    ...(data.political?.whales || []),
    ...(data.political?.capitol || [])
  ];
  const newsItems = [
    ...(data.news?.market || []),
    ...(data.news?.world || [])
  ];
  const riskEntries = Object.entries(data.risk || {});

  return (
    React.createElement('div', { className: 'dashboard' },
      React.createElement('div', { className: 'panel' },
        React.createElement('h3', null, 'Political Signals'),
        React.createElement('ul', null,
          politicalItems.map((p, i) =>
            React.createElement('li', { key: i },
              `${p.Ticker || p.ticker || p.symbol || ''} ${p.Representative || (p.metrics && p.metrics.Representative) || ''}`
            )
          )
        )
      ),
      React.createElement('div', { className: 'panel' },
        React.createElement('h3', null, 'News Feed'),
        React.createElement('ul', null,
          newsItems.map((n, i) =>
            React.createElement('li', { key: i },
              React.createElement('a', {
                href: n.url || (n.metrics && n.metrics.url),
                target: '_blank'
              }, n.title || (n.metrics && n.metrics.title))
            )
          )
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
