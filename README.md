<p align="center">
  <img src="imgs/logo.png" alt="Wing Logo">
</p>

#
Visit: [wingserver.vercel.app](https://wingserver.vercel.app)
#

## 1. Introduction

Wing is a Python CLI tool that exposes a local development server to the
public internet through a shareable URL. It is designed to be simple to
use, with no additional configuration required for typical workflows.

Wing supports forwarding both HTTP and WebSocket traffic out of the box.

## 2. CLI Client

### 2.1 Overview

Wing's CLI client connects your development machine to the central
relay. It forwards incoming requests to your local server and sends the
server's responses back through the relay to the requesting client.

The client is written in Python and requires Python 3.9 or later.

### 2.2 Installing

Wing supports macOS and Linux. Install it using the public installation
script:

``` bash
curl -fsSL https://wingserver.vercel.app/install.sh | bash
```

To verify the installation, run:

``` bash
wing --version
```

The installer creates a dedicated Python virtual environment, installs
Wing and its dependencies, and configures the `wing` command.

If the command is not recognized after installation, restart your
terminal or ensure that `~/.local/bin` is included in your `PATH`.

### 2.3 Updating

Updating Wing installs the latest release from GitHub. Run:

``` bash
curl -fsSL https://wingserver.vercel.app/install.sh | bash -s -- --update
```

### 2.4 Uninstalling

Uninstalling Wing removes its installed files, virtual environment, and
command launcher. Any manual changes to your shell configuration may
need to be removed separately.

Run:

``` bash
curl -fsSL https://wingserver.vercel.app/install.sh | bash -s -- --uninstall
```

### 2.5 Usage

Wing can be started from any working directory. Flutter mode is an
exception because it requires the path to a Flutter project.

Use the `start` command followed by the port you want Wing to expose:

``` bash
wing start <port-number>
```

For example:

``` bash
wing start 8324
```

This exposes port `8324` for external connections. Wing provides a
generated URL that can be shared to access the service over the
internet.

### 2.6 Flutter Support

Wing includes a Flutter-specific mode for previewing Flutter
applications. It builds a web version of your Flutter app, so make sure
your project is configured to support Flutter web builds.

See the [official Flutter web build
documentation](https://docs.flutter.dev/platform-integration/web/building)
for instructions.

To run Flutter mode, use:

``` bash
wing start -f <path-to-your-flutter-project>
```

You can specify the path to your Flutter project or use `.` to reference
the current directory. For example, if you're already in your Flutter
project's directory, run:

``` bash
wing start -f .
```

In Flutter mode, Wing automatically runs a Flutter build command from
your project and serves the project through a web server on port `8374`.

**Note:** Support for hot reloading is currently under development.

## 3. Contribution and Support

Wing is an open-source project. Feel free to contribute to its
development, use it, or modify it to fit your needs.

If you encounter a bug, have questions about Wing's functionality, or
simply want to get in touch, email <gerenahu1@gmail.com>.

You can also open an issue in the [Wing GitHub
repository](https://github.com/nahugere/wing). When reporting a bug,
please include a clear description and detailed steps to reproduce it.
