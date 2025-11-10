(function() {
  const API_BASE = '/analytics';
  const $ = (id) => document.getElementById(id);

  let entryMethodChart = null;
  let timePatternsChart = null;
  let directionPatternsChart = null;

  async function loadOverview() {
    try {
      const res = await fetch(`${API_BASE}/overview`);
      const data = await res.json();
      
      const stats = data.overall_stats;
      $('total-trades').textContent = stats.total_trades || 0;
      $('win-rate').textContent = stats.win_rate ? `${stats.win_rate.toFixed(1)}%` : '-';
      $('avg-pnl').textContent = stats.avg_pnl ? `$${stats.avg_pnl.toFixed(2)}` : '-';
      $('avg-r').textContent = stats.avg_r_multiple ? `${stats.avg_r_multiple.toFixed(2)}R` : '-';
      $('trades-with-method').textContent = data.trades_with_entry_method || 0;
      $('entry-method-count').textContent = data.entry_method_count || 0;
    } catch (err) {
      console.error('Failed to load overview:', err);
    }
  }

  async function loadEntryMethodStats() {
    try {
      const res = await fetch(`${API_BASE}/entry-methods`);
      const data = await res.json();
      
      const methods = data.entry_methods || [];
      
      // Update table
      const tbody = $('entry-method-tbody');
      tbody.innerHTML = '';
      for (const method of methods) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${escapeHtml(method.entry_method_name)}</td>
          <td>${method.total_trades}</td>
          <td>${method.win_rate ? `${method.win_rate.toFixed(1)}%` : '-'}</td>
          <td class="${method.avg_pnl >= 0 ? 'positive' : 'negative'}">${method.avg_pnl ? `$${method.avg_pnl.toFixed(2)}` : '-'}</td>
          <td class="${method.avg_r_multiple >= 0 ? 'positive' : 'negative'}">${method.avg_r_multiple ? `${method.avg_r_multiple.toFixed(2)}R` : '-'}</td>
          <td>${method.wins}</td>
          <td>${method.losses}</td>
        `;
        tbody.appendChild(tr);
      }
      
      // Update chart
      if (entryMethodChart) {
        entryMethodChart.destroy();
      }
      
      const ctx = document.getElementById('entry-method-chart').getContext('2d');
      entryMethodChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: methods.map(m => m.entry_method_name),
          datasets: [
            {
              label: 'Win Rate (%)',
              data: methods.map(m => m.win_rate || 0),
              backgroundColor: 'rgba(34, 197, 94, 0.5)',
              borderColor: 'rgba(34, 197, 94, 1)',
              borderWidth: 1
            },
            {
              label: 'Avg R Multiple',
              data: methods.map(m => m.avg_r_multiple || 0),
              backgroundColor: 'rgba(59, 130, 246, 0.5)',
              borderColor: 'rgba(59, 130, 246, 1)',
              borderWidth: 1,
              yAxisID: 'y1'
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: {
            legend: {
              labels: {
                color: '#eaeaea'
              }
            },
            title: {
              display: false
            }
          },
          scales: {
            x: {
              ticks: {
                color: '#eaeaea'
              },
              grid: {
                color: '#1f1f1f'
              }
            },
            y: {
              beginAtZero: true,
              title: { 
                display: true, 
                text: 'Win Rate (%)',
                color: '#eaeaea'
              },
              ticks: {
                color: '#eaeaea'
              },
              grid: {
                color: '#1f1f1f'
              }
            },
            y1: {
              type: 'linear',
              display: true,
              position: 'right',
              title: { 
                display: true, 
                text: 'Avg R Multiple',
                color: '#eaeaea'
              },
              ticks: {
                color: '#eaeaea'
              },
              grid: { 
                drawOnChartArea: false,
                color: '#1f1f1f'
              }
            }
          }
        }
      });
    } catch (err) {
      console.error('Failed to load entry method stats:', err);
    }
  }

  async function loadTimePatterns() {
    try {
      const res = await fetch(`${API_BASE}/time-patterns`);
      const data = await res.json();
      
      const patterns = data.time_patterns || [];
      if (patterns.length === 0) return;
      
      // Aggregate by session
      const sessions = ['london', 'ny', 'asian'];
      const sessionData = {
        london: { winRates: [], labels: [] },
        ny: { winRates: [], labels: [] },
        asian: { winRates: [], labels: [] }
      };
      
      for (const pattern of patterns) {
        for (const session of sessions) {
          const stats = pattern[session];
          if (stats.total_trades > 0) {
            sessionData[session].winRates.push(stats.win_rate || 0);
            sessionData[session].labels.push(pattern.entry_method_name);
          }
        }
      }
      
      if (timePatternsChart) {
        timePatternsChart.destroy();
      }
      
      const ctx = document.getElementById('time-patterns-chart').getContext('2d');
      timePatternsChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: patterns.map(p => p.entry_method_name),
          datasets: [
            {
              label: 'London Session',
              data: patterns.map(p => p.london.win_rate || 0),
              backgroundColor: 'rgba(239, 68, 68, 0.5)',
              borderColor: 'rgba(239, 68, 68, 1)',
              borderWidth: 1
            },
            {
              label: 'NY Session',
              data: patterns.map(p => p.ny.win_rate || 0),
              backgroundColor: 'rgba(34, 197, 94, 0.5)',
              borderColor: 'rgba(34, 197, 94, 1)',
              borderWidth: 1
            },
            {
              label: 'Asian Session',
              data: patterns.map(p => p.asian.win_rate || 0),
              backgroundColor: 'rgba(59, 130, 246, 0.5)',
              borderColor: 'rgba(59, 130, 246, 1)',
              borderWidth: 1
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: {
            legend: {
              labels: {
                color: '#eaeaea'
              }
            },
            title: {
              display: false
            }
          },
          scales: {
            x: {
              ticks: {
                color: '#eaeaea'
              },
              grid: {
                color: '#1f1f1f'
              }
            },
            y: {
              beginAtZero: true,
              title: { 
                display: true, 
                text: 'Win Rate (%)',
                color: '#eaeaea'
              },
              ticks: {
                color: '#eaeaea'
              },
              grid: {
                color: '#1f1f1f'
              }
            }
          }
        }
      });
    } catch (err) {
      console.error('Failed to load time patterns:', err);
    }
  }

  async function loadDirectionPatterns() {
    try {
      const res = await fetch(`${API_BASE}/direction-patterns`);
      const data = await res.json();
      
      const patterns = data.direction_patterns || [];
      if (patterns.length === 0) return;
      
      if (directionPatternsChart) {
        directionPatternsChart.destroy();
      }
      
      const ctx = document.getElementById('direction-patterns-chart').getContext('2d');
      directionPatternsChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: patterns.map(p => p.entry_method_name),
          datasets: [
            {
              label: 'Bullish (Long)',
              data: patterns.map(p => p.bullish.win_rate || 0),
              backgroundColor: 'rgba(34, 197, 94, 0.5)',
              borderColor: 'rgba(34, 197, 94, 1)',
              borderWidth: 1
            },
            {
              label: 'Bearish (Short)',
              data: patterns.map(p => p.bearish.win_rate || 0),
              backgroundColor: 'rgba(239, 68, 68, 0.5)',
              borderColor: 'rgba(239, 68, 68, 1)',
              borderWidth: 1
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: {
            legend: {
              labels: {
                color: '#eaeaea'
              }
            },
            title: {
              display: false
            }
          },
          scales: {
            x: {
              ticks: {
                color: '#eaeaea'
              },
              grid: {
                color: '#1f1f1f'
              }
            },
            y: {
              beginAtZero: true,
              title: { 
                display: true, 
                text: 'Win Rate (%)',
                color: '#eaeaea'
              },
              ticks: {
                color: '#eaeaea'
              },
              grid: {
                color: '#1f1f1f'
              }
            }
          }
        }
      });
    } catch (err) {
      console.error('Failed to load direction patterns:', err);
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  async function loadAll() {
    await Promise.all([
      loadOverview(),
      loadEntryMethodStats(),
      loadTimePatterns(),
      loadDirectionPatterns()
    ]);
  }

  // Load data on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadAll);
  } else {
    loadAll();
  }
})();

