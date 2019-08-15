# Continous Integration
During CI, several docker images are built, and a bunch of testing is performed:
- Files in this repository are linted in a variety of ways
	- Conformance with [`.editorconfig`](/.editorconfig)
	- Python formatting (PEP-8 with 120 character wide lines)
	- Python linting (pylint)
	- Python static type checking (mypy)
- All commands are sanity-checked (e.g., after running `dist-clean`, the previously checked out `llvm` folder is missing)
- And finally, all four default configurations are built ([release](/ws-config/release.toml), [profile](/ws-config/profile.toml), [debug](/ws-config/debug.toml), and [sanitized](/ws-config/sanitized.toml))

## Generated Docker Images

While the CI pushes its created docker images to the registry `eyrie.comsys.rwth-aachen.de`, it is strongly suggested to pull these images through the address `kleenet.comsys.rwth-aachen.de`, as this is the public address that (while disallowing pushes) does not require authentication from the user side. Both of these addresses are only reachable from within the COMSYS network.

Multiple tags are pushed, the purposes of which are:

- `:latest` provides a fully setup workspace with the sources checked out for the dependent projects based on the master branch
- `:latest-prebuilt` additionally contains a built release version
- `:ci` is used internally for layer-caching the ci steps
- `:$COMMIT_HASH` is an *expering* version of that specific commit hash
