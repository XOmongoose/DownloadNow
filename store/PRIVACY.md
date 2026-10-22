# Download Now Bridge — Privacy Policy

Last updated: 22 October 2026.

Download Now Bridge transfers a download URL and optional filename to the Download
Now application running on the same Windows computer at http://127.0.0.1:8765.
It does not send this information to the developer, analytics providers, or a cloud service.
The desktop downloader contacts the server hosting the file to perform the download.

When enabled, browser download interception reads download URLs, filenames and state.
The optional click capture feature reads the file link that the user clicks; it needs
optional website access granted by the user. It does not collect browsing history,
passwords or cookies, and does not transfer login sessions to the desktop application.

The extension stores a local connection credential, feature preferences, and the
latest connection/error message in browser local extension storage. Automatic pairing
reads the connection credential only from the local application's page. The credential
is verified with that application before being saved and is never sent to file servers.

The desktop application keeps download records, partial files and settings locally.
Users can remove history and optionally the downloaded files from the application.
Removing the extension removes its own browser-local settings.

The desktop updater contacts GitHub Releases to check versions and download updates.
The extension also contacts the public GitHub Releases API when checking updates,
on browser startup, when opening its popup, or approximately every six hours.
Metadata is cached locally. No download URLs, filenames, or connection credentials
are sent to GitHub. Updates require confirmation in the desktop application. A Chromium extension loaded
from the application folder receives updated files with the application and reloads
when no link handoff is pending. Other unpacked installs need a one-time folder switch.
It validates SHA-256 before preparing an update. Browser extension updates are delivered
by the applicable browser store after publication and approval.

No advertising, analytics, sale of personal information, or remote executable code
is included in the extension. The extension does not make purchases or authenticate
to user accounts. Browser store and GitHub services apply their own privacy policies.

Questions and requests: https://github.com/XOmongoose/DownloadNow/issues

The activeTab permission reads the current page URL only when the user invokes the
extension. The video button sends the selected public YouTube/Shorts or Reels page
URL to the local application. The desktop video processor contacts the video platform
and its media CDN to retrieve metadata, video and audio. It does not read browser
cookies or transfer login sessions. Optional website access also allows showing a
Download this video button on supported video pages.

Connected extensions send their running version, browser family and managed-folder
status to the local application to acknowledge synchronized updates. These acknowledgements
expire after two minutes, remain in application memory and are never sent to GitHub
or the developer. The application page requests local synchronization every two seconds
while visible; a one-minute alarm provides a fallback.
