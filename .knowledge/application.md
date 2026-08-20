# Local application

Run `./tekt.observer up` and open `http://127.0.0.1:8091`. On a fresh checkout the launcher installs and builds frontend dependencies, seeds the three canonical watchers, and serves the React application and JSON API from one loopback origin.

The first screen is a unified signal inbox with nine realistic starter items. Search focuses with `/`; Escape closes dialogs. Watcher filters, responsive navigation, light/dark themes, watcher health and pause controls, operations, signal scores, and provenance are available immediately. The Digests screen creates persisted briefs from the strongest active signals. The Exports screen creates and downloads deterministic, hash-verified handoff bundles.

After a live pipeline run, connect its organized artifacts to the app with `./tekt.observer ingest --scratch tests/tmp/starter-workflows`. The importer journals normalized live items, run records, scores, and provenance; removes starter samples; preserves Save/Dismiss status across repeat imports; increments the workspace revision; and compacts a new snapshot. The Inbox's **Load latest run** action performs the same import for the standard starter-workflow location.

Save and Dismiss call `PATCH /api/v1/items/<id>`. The server validates the mutation, appends and fsyncs the immutable item event, increments the workspace revision through another journal event, and only then acknowledges the request. Reloading reconstructs the same state from the latest snapshot plus later events.

The server deliberately binds only to loopback. Hosted collaboration will use the PocketBase projection and authentication boundary; do not expose this local server directly to a network.
