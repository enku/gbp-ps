const gradientColors = JSON.parse(document.getElementById('gradientColors').textContent);
const tbody = document.getElementById('processes');
const query = `
query BuildProcesses($machine: String = null) {
  buildProcesses(machine: $machine) {
    machine
    id
    buildHost
    package
    phase
    startTime
  }
}`;
const buildPhases = [
  'pretend',
  'setup',
  'unpack',
  'prepare',
  'configure',
  'compile',
  'test',
  'install',
  'package',
  'instprep',
  'preinst',
  'postinst',
];
const colorMap = buildPhases.reduce((acc, phase, index) => {
  acc[phase] = gradientColors[index];
  return acc;
}, {});
let interval;

/*
 * Calculate the elapsed time since the given dateString
 *
 * Time is returned in HH:MM:SS format
 */
function elapsed(timeString, now) {
  const time = new Date(timeString);
  const elapsedMilliseconds = now - time;
  const elapsedSeconds = Math.floor(elapsedMilliseconds / 1000);
  const hours = Math.floor(elapsedSeconds / 3600);
  const minutes = Math.floor((elapsedSeconds % 3600) / 60);
  const seconds = elapsedSeconds % 60;

  return [
    String(hours).padStart(2, '0'),
    String(minutes).padStart(2, '0'),
    String(seconds).padStart(2, '0'),
  ].join(':');
}

function setProcesses(processes, now) {
  const rows = processes.map((process) => {
    const { phase } = process;
    const tr = document.createElement('tr');
    const index = buildPhases.indexOf(phase);
    let progressWidth = 100;
    let progressClass = 'progress-bar progress-bar-striped progress-bar-animated';
    let progressColor = gradientColors[0];

    if (index >= 0) {
      progressWidth = Math.floor(((index + 1) / buildPhases.length) * 100);
      progressColor = colorMap[phase];
      progressClass = 'progress-bar';
    }
    tr.innerHTML = `
      <td>${process.machine}</td>
      <td class="numeric">${process.id}</td>
      <td class="package">${process.package}</td>
      <td class="numeric">${elapsed(process.startTime, now)}</td>
      <td class="phase">${phase}</td>
      <td class="phase-progress">
        <div class="progress">
            <div class="${progressClass}" role="progressbar" style="background-color: ${progressColor}; width: ${progressWidth}%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="${buildPhases.length}"></div>
        </div>
      </td>
    `;
    return tr;
  });
  tbody.replaceChildren(...rows);
}

function getInterval() {
  const defaultInterval = '500';
  const currentUrl = window.location.href;
  const url = new URL(currentUrl);
  const params = new URLSearchParams(url.search);
  const param = params.get('update_interval') || defaultInterval;

  return parseInt(param, 10);
}

function getProcesses() {
  interval = interval || getInterval();

  fetch('/graphql', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ query }),
  })
    .then((r) => r.json())
    .then((result) => {
      const now = new Date();
      setProcesses(result.data.buildProcesses, now);
    })
    .catch(() => {})
    .finally(() => setTimeout(getProcesses, interval));
}

document.addEventListener('DOMContentLoaded', getProcesses);
