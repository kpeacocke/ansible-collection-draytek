from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
import re


def main():
    module = AnsibleModule(argument_spec=dict(command=dict(required=True, choices=['sys iface', 'show status'])))
    try:
        output = Connection(module._socket_path).run_commands(commands=[dict(
            command=module.params['command'], prompt=r'(?!)', answer='', strip_prompt=False)])[0]
        markers = re.findall(r"--- MORE ---[^\r\n]{0,180}", output)
        module.exit_json(changed=False, markers=markers, marker_count=len(markers))
    except Exception:
        module.fail_json(msg='Pager probe failed; raw device output suppressed')


if __name__ == '__main__':
    main()
