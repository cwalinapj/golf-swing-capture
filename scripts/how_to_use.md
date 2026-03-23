Make them executable:

chmod +x scripts/*.sh

Typical usage:

scripts/setup.sh
source scripts/export_take_env.sh
scripts/record.sh

That gives you a nice GitHub-friendly pattern:
	•	setup.sh installs everything
	•	export_take_env.sh holds your field defaults
	•	record.sh is your one-command launch
	•	run.sh is the underlying runner

A good next addition would be a scripts/run_roof.sh once you want the roof camera launched alongside the impact rig.
