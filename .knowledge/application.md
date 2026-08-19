# Local application

Run `./tekt.observer up` and open `http://127.0.0.1:8091`. On a fresh checkout the launcher installs and builds frontend dependencies, seeds the three canonical watchers, and serves the React application and JSON API from one loopback origin.

The first screen is a unified signal inbox with nine realistic starter items. Search focuses with `/`; Escape closes dialogs. Watcher filters, responsive navigation, light/dark themes, watcher health, operations, signal scores, and provenance are available immediately.

Save and Dismiss call `PATCH /api/v1/items/<id>`. The server validates the mutation, appends and fsyncs the immutable item event, increments the workspace revision through another journal event, and only then acknowledges the request. Reloading reconstructs the same state from the latest snapshot plus later events.

The server deliberately binds only to loopback. Hosted collaboration will use the PocketBase projection and authentication boundary; do not expose this local server directly to a network.
