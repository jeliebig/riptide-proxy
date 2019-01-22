var project_name = '{{ project["name"] }}';
var host = window.location.host;
var ws = new WebSocket('ws://' + host + '/___riptide_proxy_ws');
ws.onopen = function () {
    // Start: Register project name
    ws.send(JSON.stringify({method: 'register', project: project_name}));
};
ws.onmessage = function (ev) {
    message = JSON.parse(ev.data);
    if (message.status === "ready") {
        // Start!
        ws.send(JSON.stringify({method: 'start'}))
    } else if (message.status === "update") {
        // Update progress bars
        var service = message.update.service;
        if (message.update.finished) {
            finish(get(service))
        } else if (message.update.error) {
            error(get(service), message.update.error)
        } else if (message.update.status) {
            // message.update.status -> {steps, current_step, text}
            update(get(service), message.update.status)
        }
    } else if (message.status === "success") {
        // Done!
        document.querySelectorAll('#autostart-table [data-service]').forEach(function (elem) {
            finish(elem);
        });
        location.reload();
    }
};
ws.onclose = function (ev) {
    var reason = 'Unknown';
    if (ev.reason) {
        reason =  + ev.reason;
    }
    document.getElementById('autostart-error').innerHTML =
        'Connection to Proxy closed. Reason: ' + reason + ' (Code: ' + ev.code + ')';
};


function get(serviceName) {
    return document.querySelector('#autostart-table [data-service="' + serviceName + '"]');
}

function finish(serviceElem) {
    var current_step = serviceElem.querySelector(".col-step .k");
    var steps = serviceElem.querySelector(".col-step .n");
    var progress = serviceElem.querySelector(".col-progress .wrapper .progress");

    current_step.innerHTML = steps.innerHTML;
    progress.style.width = '100%';
    progress.classList.remove('yellow');
    progress.classList.remove('red');
    progress.classList.add('green');
}

function error(serviceElem, errorMsg) {
    var progress = serviceElem.querySelector(".col-progress .wrapper .progress");
    var statusText = serviceElem.querySelector(".at-entry-status");

    statusText.innerHTML = errorMsg;
    progress.classList.remove('yellow');
    progress.classList.remove('green');
    progress.classList.add('red');
}

function update(serviceElem, status) {
    // status -> {steps, current_step, text}
    var current_step = serviceElem.querySelector(".col-step .k");
    var steps = serviceElem.querySelector(".col-step .n");
    var progress = serviceElem.querySelector(".col-progress .wrapper .progress");
    var statusText = serviceElem.querySelector(".at-entry-status");

    steps.innerHTML = status.steps;
    current_step.innerHTML = status.current_step;
    statusText.innerHTML = status.text;
    progress.style.width = Math.round(status.current_step / status.steps * 100) + '%';
    progress.classList.remove('green');
    progress.classList.remove('red');
    progress.classList.add('yellow');
}