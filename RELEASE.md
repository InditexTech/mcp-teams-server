### Release process

Review and integrate desired works and PRs into main branch before launching a release.

Release process is triggered from a PR labeled with "kind/release" label.

Please review [version](./pyproject.toml) in project section because tag is inferred from that value

Before the release PR is merged or closed, ensure the linked issue is traceable from the PR and issue history. Use a closing keyword plus the issue number in the PR body (for example, `Closes #123`), or otherwise add a PR comment to the issue naming the closing PR. Close the issue explicitly if automatic linking is unavailable or lost.

Once the PR is closed, the release process will begin.

To repeat a failing release, remember to remove the `version` tag previously created.
