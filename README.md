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

![Screenshot](docs/screenshot.png)

**gbp-ps** is a `ps`-like subcommand for the [Gentoo Build Publisher
CLI](https://github.com/enku/gbpcli). When installed, all you need to do is
run `gbp ps` to see all the packages being built, for which machines they're
being built for, and what phase of the build process the package is in.

## How does it work?

The gbp-ps package includes a plugin for Gentoo Build Publisher that includes
a table for keeping package build "processes" and a GraphQL interface for
updating the process table. Each machine's build then updates the table via
GraphQL during each phase of the build. This is done via the
`/etc/portage/bashrc` file.  For example I make the following change to my
[machines repo](https://github.com/enku/gbp-machines):

```diff
diff --git a/Makefile b/Makefile
index 74921dd..55280d4 100644
--- a/Makefile
+++ b/Makefile
@@ -14,6 +14,9 @@ container := $(machine)-root
 chroot := buildah run \
   --env=BINPKG_COMPRESS=xz \
   --env=BINPKG_COMPRESS_FLAGS="-9 $(XZ_DEFAULTS)" \
+  --env=BUILD_MACHINE=$(machine) \
+  --env=BUILD_NUMBER=$(BUILD_NUMBER) \
+  --env=BUILD_HOST=$(shell hostnamectl hostname) \
   --mount=type=tmpfs,tmpfs-mode=755,destination=/run \
   --volume /proc:/proc \
   --volume /var/lib/jenkins/distfiles:/var/cache/distfiles \
diff --git a/base/configs/etc-portage/bashrc b/base/configs/etc-portage/bashrc
new file mode 100644
index 0000000..b4dff41
--- /dev/null
+++ b/base/configs/etc-portage/bashrc
@@ -0,0 +1,11 @@
+# This is ugly :(
+if [[ ${EBUILD_PHASE} != depend ]]; then
+    WGET_BODY=\{\"query\":\ \"mutation\ \{addBuildProcess\(process:\{machine:\\\"${BUILD_MACHINE}\\\",buildHost:\\\"${BUILD_HOST}\\\",package:\\\"${P}\\\",id:\\\"${BUILD_NUMBER}\\\",phase:\\\"${EBUILD_PHASE}\\\",startTime:\\\""$(date -u +%Y-%m-%mT%H:%M:%S.%N+00:00)"\\\"\}\)\{message\}\}\",\ \"variables\":\ null\}
+    wget \
+        --output-document=- \
+        --no-check-certificate \
+        --header="Content-type: application/json" \
+        --method=POST \
+        --body-data="${WGET_BODY}" \
+        http://gbp/graphql
+fi
```

The changes to the `Makefile` are to include some needed environment variables
to the build container. Then I add a `/etc/portage/bashrc` that uses the
included environment variables in addition to ebuild environment variables to
make a GraphQL query to the GBP server.  This is done for each phase (except
"depend") of the build process.

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
sudo -u gbp -H ./bin/pip install git+https://github.com/enku/gbp-ps
```

Now add `"gbp_ps"` to your `INSTALLED_APPS`:

```sh
$EDITOR djangoproject/settings.py
```

Restart your web app.

```sh
systemctl restart gentoo-build-publisher-wsgi.service
```

Now the server side should be good to go.

For you individual builds you will need to make the above changes to your
machine repo's `Makefile` and each machine's `/etc/portage/bashrc` Be sure to
change the wget URL to use the actual name/address of your GBP instance (or
`localhost` if your client and server are on the same machine.

Start a machine build that will actually build some packages. Then,

```sh
gbp ps
```

This should display the process table.  When no processes are building the
output will be empty.
