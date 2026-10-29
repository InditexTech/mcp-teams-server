### Release process

Review and integrate desired works and PRs into main branch before launching a release.

Release process is triggered from a PR labeled with "kind/release" label.

Please review [version](./pyproject.toml) in project section because tag is inferred from that value

Once the PR is closed, the release process will begin.

To repeat a failing release, remember to remove the `version` tag previously created.
