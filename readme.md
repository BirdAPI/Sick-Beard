Sickbeard + XBMC Watched Status Integration
=====

The idea behind this fork is to more closely integrate Sickbeard with XMBC, by providing XMBC watched statuses on the various pages of Sickbeard , so you can quickly see which episodes you have watched, directly from Sickbeard !

At the moment this code is very experimental, and a lot of stuff is hard coded and will need a new options page to handle a lot of settings.  Currently I am only adding support for XBMC's that are setup to use a MySQL server (not standard, but thats what mine uses since i have it synced with multiple computers), but in the future this could extend to the ones using SQLite (xbmc's default, same as what Sickbeard uses).

One of the pitfalls of the MySQL code is that it requires the MySQLdb module from python, which can be a little tricky to get installed.

FUTURE TODOS:
- Add settings page for server settings, etc
- Support XBMC SQLite databases
- Merge into official Sickbeard once complete


Visit the official Sickbeard:
https://github.com/midgetspy/Sick-Beard
http://code.google.com/p/sickbeard/
