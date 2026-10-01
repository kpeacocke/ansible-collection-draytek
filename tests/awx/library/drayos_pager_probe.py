from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
import re


def main():
    module = AnsibleModule(argument_spec=dict(command=dict(required=True, choices=['sys iface', 'show status'])))
    try:
        connection = Connection(module._socket_path)
        connection.get_capabilities()
        output = connection.run_commands(commands=[module.params['command']])[0]
        markers = re.findall(r"--- MORE ---[^\r\n]{0,180}", output)
        module.exit_json(changed=False, markers=markers, marker_count=len(markers))
    except Exception as exc:
        match = re.search(r'PAGER_SHAPE:(.*)', str(exc))
        module.exit_json(changed=False, diagnostic=match[1] if match else re.sub(r'[A-Za-z0-9_]+', lambda m: m[0] if m[0] in {'method', 'not', 'found', 'socket', 'timeout', 'command', 'run_commands', 'get_capabilities', 'NoneType', 'attribute', 'object', 'has', 'file', 'such', 'No', 'authentication', 'failed'} else 'X', str(exc)))


if __name__ == '__main__':
    main()
