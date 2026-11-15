# Verda CPU deployment

**Current owner-authorized access mode (15 November): public demo, no Basic Auth.**
Do not rerun `protect` during deployment. The historical Basic Auth setup below
is retained for provenance. The protected verifier’s 401 assertion must be
adapted to expect anonymous 200 for this public release; retain the native,
preview, review/export, restart and counter checks. See
`docs/delivery/deployment-verification.md` for the current release record.

This deployment uses one on-demand `CPU-TURIN.4V.16G` VM, a 55 GB OS volume,
and the public preview dataset. It does not require a GPU or an external database.
The frontend and API share one origin. SQLite and uploaded files persist in the
host's `/srv/stoa/data/runtime` through container restarts.

The protected local configuration is `~/.config/stoa-junction-2026/secrets.env`.
It needs `VERDA_CLIENT_ID`, `VERDA_CLIENT_SECRET`, and `OPENAI_API_KEY`. Cloud
credentials stay local; only the OpenAI runtime key is transferred over SSH.
Deployment IDs and the unique SSH-key path are recorded in the protected local
`~/.config/stoa-junction-2026/verda-deployment.json`. Do not commit that directory.

```bash
python3 ops/deploy_verda.py inspect
python3 ops/deploy_verda.py create
python3 ops/deploy_verda.py status
python3 ops/deploy_verda.py bootstrap
python3 ops/deploy_verda.py sync
python3 ops/deploy_verda.py protect
python3 ops/deploy_verda.py start
```

Wait until the VM is running and SSH is ready before bootstrap. The application
binds only to localhost. Caddy provides public HTTPS at an IP-based `sslip.io`
hostname and requires HTTP Basic authentication for every application request,
including billable model endpoints. Credentials are generated into the protected
local `~/.config/stoa-junction-2026/access.env`; the password is never printed or
embedded in a URL. HTTP redirects to HTTPS. Public challenge drawings are the
initial dataset. Verify certificate issuance and unauthenticated HTTP 401 before
sharing the URL. DNS and public ACME certificate availability are external
dependencies. `protect` reuses the existing access password when rerun.

To deploy code updates, repeat `sync` and `start`. Runtime files are kept outside
the container. These SSH-only operations keep working after the short-lived
Verda Cloud credential expires; `inspect`, `create` and `status` need an active
Cloud credential. Check `/var/log/stoa-build.log` over SSH for build failures and
`docker logs stoa-junction` for application logs. The container restarts after a
host reboot through Docker's restart policy.

Verify the deployment without any model requests:

```bash
python3 ops/verify_remote.py --exercise --restart
```

This checks authentication, the 913-file preview, a native IFC count and evidence,
the PNG preview, a review followed by restoration, JSON export and persistence
through a container restart.

## End the deployment and its charges

In Verda Console, select the `stoa-junction-*` CPU instance in the project, choose
**Delete instance**, and select its named 55 GB OS volume for deletion when the
dataset/runtime no longer need retaining. Review both compute and storage lists
after deletion. Deleting only the container or shutting down the VM does not
end VM billing; retaining its volume continues storage billing. The protected
deployment-state file records the exact instance and volume IDs. No automatic
top-up or long-term contract is configured by these scripts.

Creation mutations are never retried automatically. If creation times out, look
for the recorded unique hostname in Verda before trying again. Stopping/shutting
down a Verda instance still incurs compute charges; delete it in Console to end
compute billing and explicitly select volumes to delete if their data is no
longer needed. The script never removes resources or enables automatic top-ups.

The public API contract is documented at https://api.verda.com/v1/docs.
