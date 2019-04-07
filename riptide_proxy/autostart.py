import json
import logging
from tornado import websocket

from riptide_proxy.project_loader import resolve_project

logger = logging.getLogger('tornado_proxy')


def try_write(client, msg):
    """Try to send a message over a Websocket and silently fail."""
    try:
        client.write_message(msg)
    except:
        pass


def build_status_answer(service_name, status, finished):
    """TODO DOC"""
    if finished:
        if status:
            update = {
                'service': service_name,
                'error': str(status)
            }
        else:
            # no error
            update = {
                'service': service_name,
                'finished': True
            }
            pass
    else:
        # update
        update = {
            'service': service_name,
            'status': {
                'steps': status.steps,
                'current_step': status.current_step,
                'text': status.text
            }
        }
        pass
    return {
        'status': 'update',
        'update': update
    }


# TODO DOC
class AutostartHandler(websocket.WebSocketHandler):

    def __init__(self, application, request, config, engine, runtime_storage, **kwargs):
        super().__init__(application, request, **kwargs)
        self.project = None
        self.config = config
        self.engine = engine
        self.runtime_storage = runtime_storage

    clients = {}

    # True if any of the WebSocket object coroutines currently starts the project
    running = False

    def check_origin(self, origin):
        return True

    def open(self):
        logger.debug('WS: Connection from %s. Waiting for project name...' % self.request.remote_ip)

    def on_close(self):
        if self.project:
            logger.debug('WS: Connection from %s for %s CLOSED' % (self.request.remote_ip, self.project["name"]))

            # Remove from list of clients
            if self in self.__class__.clients:
                self.__class__.clients[self.project["name"]].remove(self)

    async def on_message(self, message):
        decoded_message = json.loads(message)

        # Register a project to monitor for this websocket connection
        if decoded_message['method'] == "register":  # {method: register, project: ...}
            project, _ = resolve_project(decoded_message['project'], None, self.runtime_storage, logger)
            if project is None:
                self.close(403, 'Project not found.')
                return

            self.project = project

            logger.debug('WS: Connection from %s for %s' % (self.request.remote_ip, self.project["name"]))

            # Add to list of clients
            if self not in self.__class__.clients:
                if self.project["name"] not in self.__class__.clients:
                    self.__class__.clients[self.project["name"]] = []
                self.__class__.clients[self.project["name"]].append(self)

            self.write_message(json.dumps({'status': 'ready'}))

        # Start the registered project
        elif decoded_message['method'] == "start" and self.project:  # {method: start}
            p_name = self.project["name"]
            logger.debug('WS: Start Request for %s from %s' % (p_name, self.request.remote_ip))
            if not self.__class__.running:
                logger.debug('WS: STARTING project %s!', p_name)
                self.__class__.running = True
                had_an_error = False
                try:
                    services = self.project["app"]["services"].keys()
                    async for service_name, status, finished in self.engine.start_project(self.project, services):
                        for client in self.__class__.clients[p_name]:
                            try_write(client, json.dumps(build_status_answer(service_name, status, finished)))
                        if status and finished:
                            had_an_error = True
                except Exception as err:
                    logger.warning('WS: Project %s start ERROR: %s', (p_name, str(err)))
                    for client in self.__class__.clients[p_name]:
                        try_write(client, json.dumps({'status': 'error', 'msg': str(err)}))
                else:
                    if not had_an_error:
                        # Finished
                        logger.debug('WS: Project %s STARTED!', p_name)
                        for client in self.__class__.clients[p_name]:
                            try_write(client, json.dumps({'status': 'success'}))
                    else:
                        logger.debug('WS: Project %s ERROR!', p_name)
                        for client in self.__class__.clients[p_name]:
                            try_write(client, json.dumps({'status': 'failed'}))
                self.__class__.running = False
