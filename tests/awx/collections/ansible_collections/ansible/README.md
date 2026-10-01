This namespace directory exists before playbook startup so the validation
playbook can install its declared ansible.netcommon dependency here before
loading network_cli. The job's temporary project is the only install target.
