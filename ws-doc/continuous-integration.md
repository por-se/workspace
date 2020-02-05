# Continuous Integration
During CI, several docker images are built, and a bunch of testing is performed:
- Files in this repository are linted in a variety of ways
	- Conformance with [`.editorconfig`](/.editorconfig)
	- Python formatting (PEP-8 with 120 character wide lines)
	- Python linting (pylint)
	- Python static type checking (mypy)
- All commands are sanity-checked (e.g., after running `dist-clean`, the previously checked out `llvm` folder is missing)
- And finally, all four default configurations are built ([release](/ws-config/release.toml), [profile](/ws-config/profile.toml), [debug](/ws-config/debug.toml), and [sanitized](/ws-config/sanitized.toml))

## Generated Docker Images

Two docker images are generated and pushed to the GitLab registry.

The first image uses the name of the repository and pushes several tags:
- `:latest` provides a fully setup workspace with the sources checked out for the dependent projects based on the master branch
- `:latest-prebuilt` additionally contains a built release version

Additionally, the CI will internally use the image corresponding to the name of the repository with an additional `/ci` to push several CI related tags. These tags should be cleaned up regularly to prevent them from accumulating.
- `:latest` is used internally for layer-caching the ci steps
- `:$COMMIT_HASH` is used to propagate the image down the CI stages
