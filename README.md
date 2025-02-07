# gbp-ps - A gbpcli plugin to display your Gentoo Build Publisher processes

Say you are a [Gentoo Build
Publisher](https://github.com/enku/gentoo-build-publisher) user. Inevitably
the time comes when you notice some activity on your build machine. For
example the fans start spinning up. It goes on for a while and you start to
wonder what's going on.

So you open a tab in your browser, point it at your Jenkins instance. You see
there's a build happening. But what's being built?  You click on the job. Then
go to the console output. Ok now you can see what packages are being built. If
only there were a better way.

Now there is.

<p align="center">
<img src="https://raw.githubusercontent.com/enku/screenshots/refs/heads/master/gbp-ps/screenshot.gif" alt="gbpcli screenshot" width="100%">
</p>

**gbp-ps** is a `ps`-like subcommand for the [Gentoo Build Publisher
CLI](https://github.com/enku/gbpcli). When installed, all you need to do is
run `gbp ps` to see all the packages being built, for which machines they're
being built for, and what phase of the build process the package is in.

## How does it work?

The gbp-ps package includes a plugin for Gentoo Build Publisher that includes
a table for keeping package build "processes" and a GraphQL interface for
updating the process table. Each machine's build then updates the table via
GraphQL during each phase of the build. This is done via the
`/etc/portage/bashrc` file.  For example each machines' build processes you'd
want to query:

```console
gbp-machines $ gbp ps-dump-bashrc >> base/configs/etc-portage/bashrc
# Check the above file to ensure, e.g., the URL is correct
git add base/configs/etc-portage/bashrc
git commit -m "base: add gbp-ps to bashrc"
git push
```

The contents of the `bashrc` send a GraphQL call to GPB. This is done for each
phase (except "depend") of the build process.

gbp-ps includes a Django package that adds the GraphQL interface to Gentoo
Build Publisher and maintains the process table.

So now that we have a process table and a way for the build containers to
update it, we need a method to query the table. Again the GraphQL interface
provides the interface to query the table. For the client side, gbp-ps adds a
subcommand to gbpcli ("`ps`") that makes the query and displays it. And voila!

# Installation

This assumes you already have a working Gentoo Build Publisher installation.
If not refer to the GBP Install guide first.

Install the gbp-ps package onto the GBP instance.

```sh
cd /home/gbp
sudo -u gbp -H git -C gentoo-build-publisher pull
sudo -u gbp -H ./bin/pip install gbp-ps[server]
```

Restart your web app.

```sh
systemctl restart gentoo-build-publisher-wsgi.service
```

Now the server side should be good to go.

For you individual builds each machine's
`<machine>/configs/etc-portage/bashrc` contain the script above. If your
machine doesn't have the file already then create it. Be sure to change the
wget URL to use the actual name/address of your GBP instance (or `localhost`
if your client and server are on the same machine.

Start a machine build that will actually build some packages. Then,

```sh
gbp ps
```

This should display the process table.  When no processes are building the
output will be empty.

There is also a "continuous" mode where gbp-ps will display the ebuild processes
continuously on the screen:

```sh
gbp ps -c
```

To show the processes accompanied by a process bar, pass the `--progress`
flag.

## Run without Gentoo Build Publisher

**gbp-ps** is also capable of working "locally" without the need of a Gentoo
Build Publisher instance. This allows you to use gbp-ps on a local machine.
To do so, from the machine you want to run gbp-ps:

```console
gbp ps-dump-bashrc --local >> /etc/portage/bashrc
```

Now whenever you run an `emerge` command, you should be able, in another
terminal, run `gbp ps` to display the build processes from that command. Note
that the local functionality is currently experimental.


## "pipeline" process

If you've seen screenshots of **gbp-ps** that shows a "pipeline" process, that
is being emitted from the Jenkins or GBP and not from the build container.
The method for doing this will be documented at a later time.
