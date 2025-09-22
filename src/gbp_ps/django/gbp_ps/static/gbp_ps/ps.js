const gradientColors = JSON.parse(document.getElementById('gradientColors').textContent);
const defaultInterval = JSON.parse(document.getElementById('defaultInterval').textContent);
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

function getRowId(process) {
  const sanitizedPackage = process.package.replace(/\//g, '_');

  return `${process.machine}_${process.id}_${sanitizedPackage}`;
}

function removeGoneProcesses(processes) {
  const rowIds = Array.from(processes, (process) => getRowId(process));

  tbody.querySelectorAll('tr').forEach((row) => {
    if (rowIds.indexOf(row.id) < 0) {
      tbody.removeChild(row);
    }
  });
}

function setProcesses(processes, now) {
  removeGoneProcesses(processes);

  processes.map((process) => {
    const { phase } = process;
    let progressWidth = 100;
    let progressClass = 'progress-bar progress-bar-striped progress-bar-animated';
    let progressColor = gradientColors[0];
    const index = buildPhases.indexOf(phase);

    if (index >= 0) {
      progressWidth = Math.floor(((index + 1) / buildPhases.length) * 100);
      progressColor = colorMap[phase];
      progressClass = 'progress-bar';
    }
    const progressBar = `
            <div class="${progressClass}" role="progressbar" style="background-color: ${progressColor}; width: ${progressWidth}%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="${buildPhases.length}"></div>`;
    const rowId = getRowId(process);
    const elapseTime = elapsed(process.startTime, now);
    let tr = document.getElementById(rowId);

    if (tr) {
      tr.querySelector('td.elapsed').textContent = elapseTime;
      const phaseElem = tr.querySelector('td.phase');

      if (phaseElem.textContent !== phase) {
        phaseElem.textContent = process.phase;
        const progress = tr.querySelector('div.progress');
        progress.innerHTML = progressBar;
      }
      return phase;
    }
    tr = document.createElement('tr');
    tr.id = rowId;
    tr.innerHTML = `
      <td>${process.machine}</td>
      <td class="numeric">${process.id}</td>
       <td class="package">${process.package}</td>
       <td class="elapsed numeric">${elapseTime}</td>
       <td class="phase">${phase}</td>
       <td class="phase-progress">
         <div class="progress">
           ${progressBar}
         </div>
       </td>
     `;
    tbody.appendChild(tr);
    return phase;
  });
}

function getInterval() {
  const url = new URL(window.location.href);
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
