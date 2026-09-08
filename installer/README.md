# Publication and recovery

An install stages the library, scripts and browser distribution before
replacing them. It takes `tickets_install_guard.installation_lock` before
any run lock; issuance, dispatch and nonterminal lifecycle transitions use
the same ordering. Missing or
unreadable ticket state refuses publication. Every active pinned invocation
or role-bearing worker, including a pinned frame or suspended assignment,
conservatively protects the whole existing payload: an emitted close command
also depends on the runtime scripts and private Python dependencies.
The private runtime action is rechecked under this lock: creation or repair
refuses while those references exist; verified reuse does not enter the
runtime replacement path. Verified unpinned role-none frames and
unstamped pending drafts do not block an update; sealing takes the same
installation lock before creating their pins. Unknown identities or malformed
pins fail closed. Identical bytes can receive a new receipt without
moving the active directories. A payload change requires closing or
retiring its active owners through the ordinary lifecycle.

The flat script directory may contain operator-authored helpers. A newly
shipped script with differing bytes at an unowned destination refuses with
the exact conflicting path, leaving the helper and receipt intact. Resolve
that collision explicitly before retrying; noncolliding helpers are preserved.

The first upgrade from writers that lack this lock (including the lifecycle
writer) refuses a changed payload or private runtime replacement even if the
current census is empty. No flag disables this check.
For that one migration, the operator must arrange an offline maintenance
window:

1. Finish or retire every role-bearing or pinned nonterminal assignment
   and frame. Verified unpinned role-none frames and unstamped pending
   drafts may remain. Preserve the
   installed state directory; removing it is not a way to pass the census.
2. Stop every host session, scheduler and standalone process capable of
   invoking the old installation, and prevent new invocations for the
   maintenance window. This is an operator condition, not a fact an empty
   census or a process-list snapshot proves.
3. Resolve the installation home and move its `bin` directory intact to a
   distinct sibling backup, for example `bin-offline-20260908`. Do this
   only after verifying both absolute paths are inside that home. Keep
   the old library, receipt, state and parked scripts intact.
4. From the accepted source checkout, run `install.py --accepted-source
   COMMIT` through the verified interpreter. With the old entry directory
   parked and its clients stopped, no old entrypoint is available for new
   launches. The normal census and transaction checks still apply.
5. Run `install.py doctor` and an installed entry probe before reopening
   clients. Retain the parked scripts until those checks succeed. If the
   install refuses before publication, restore the parked directory while
   clients remain stopped.

On a failed rollback, the error names `.install-transaction-<id>` and its
`recovery.json`. Keep that directory: it contains the complete prior
payload directories and copies of changed external surfaces. Further
installation refuses while this recovery map remains. With clients stopped,
restore the recorded backups to the recorded live paths (parking any new
partial payload first), restore the recorded surface copies, and verify
the old receipt and entrypoints. Only then archive the transaction directory
outside the installation home and retry. Never delete the sole backup to
make a retry pass.
