# The Process of GBP Processes

This document is mainly intended for developers wishing to know how gbp-ps is
structured and how it works.

This project is structured as a plugin or extension. It's actually three
plugins in one:

    - A Django app. Thus needs to be added to `INSTALLED_APPS`. This however,
      is only needed if the storage backend selected is the Django ORM (see
      below). However this is the default.
    - A Gentoo Build Publisher (server) GraphQL plugin. This project exposes a
      `schema.graphql` file via the `"gentoo_build_publisher.graphql_schema"`
      entry point. When installed, Gentoo Build Publisher will pick this up
      and add it to it's GraphQL schema.  This is a new feature added to GBP
      in [this commit](https://tinyurl.com/3nc7ase9).
    - A [gbpcli](https://github.com/enku/gbpcli) plugin that adds a `ps`
      subcommand to the command-line interface.


## Process Table

The process table is the central point of gbp-ps.  The idea is that the build
containers constantly update the process table in each phase of an ebuild
(except for the depend phase).  Each process contains the following fields:

    - `machine`: the machine the job is being run on
    - `id`: the (Jenkins) build id
    - `build_host`: the hostname of the machine running the (Jenkins) job
    - `package`: the package (CPV) being built
    - `phase`: the ebuild phase of the package being built
    - `start_time`: the timestamp when the ebuild started emerging

The datatype `BuildProcess` wraps these values (defined in `types.py`).

Each container is expected to have an `/etc/portage/bashrc` that, when run by
the portage, makes a `addProcess` GraphQL call to Gentoo Build Publisher with
the fields above.  If the `(machine, id, package)` triplet doesn't exist in
the table it is added, otherwise it is updated. Updates however only update
the `phase`. This especially means that `start_time` is never updated and so
is always the time of the first phase of the build.

Another feature of `addProcess` is that if any `(machine, package)` pair
exists in the table but for a different `id` they are removed from the table
prior to adding the new one. This is because any existing builds for a package
with a different `id` are considered to be failed builds. There is no "failed
build" phase (that I now of) and so this is the only way to removed a failed
build from the process table. In fact if a `(machine, package)` build fails
and there is no subsequent build to replace it, it will remain in the process
table (a zombie?). However for the Redis backend (see below) the zombie will
eventually expire.


## getProcesses

The `buildProcess` GraphQL call is the method to write to the process table.
The method to read from the process table is the `getProcesses` call. This
returns a list of the processes in the table. By default processes which are
in a "final" phase are excluded unless the `includeFinal` argument is passed
and is `true`. For the set of phases that are considered "final" see
`types.py`


## Storage backends

There are a couple of storage backends for the process table. Each storage
backend has in interface, `RepositoryType` defined in `types.py`. The default
storage backend is the Django ORM, which manages the process table in a
relational database as part of the Gentoo Build Publisher Django app.  However
because I want to eventually not have to depend on Django, and because Redis
is arguably a better fit, there is also a Redis backend. The advantages of the
Redis backend are performance (though this has not been measured), the ability
to "reset" the table on reboots, and the ability for processes to auto-expire
after a given time. Both backends are defined in `repository.py`. 

Currently the the Django ORM is the default and the only way to switch to the
Redis backend is to define the environment variable `GBP_PS_REDIS_URL`
pointing to a Redis instance. For the redis backend we use a simple key/value
store for processes. The key looks like this:

```
<prefix>:<machine>:<package>:<build_id>
```

Where `<prefix>` is `"gbp-ps"` by default but can be changed using the
`GBP_PS_REDIS_KEY` environment variable. The values look like this:

```javascript
{
    "build_host": "jenkins",
    "phase": "compile",
    "start_time": "2023-11-18T16:58:51.399287+00:00"
}
```

These values are stored as JSON byte strings. For each record, the key and
value can be combined to create a `BuildProcess` object.

The `RepositoryType` interface currently does not have any mechanisms for
removing data from the process table except for the `clear()` method which
clears the entire table and is only used for tests. There's no particular
reason for this other than there is nothing needing to do this yet.


## gbpcli subcommand

The gbpcli subcommand, `ps` is defined in `cli.py` and is exposed via the
"gbpcli.subcommands" entry point. It's main job is to call the `getProcesses`
GraphQL query and output the results. There is a "continuous" mode that
constantly queries and updates the output. This subcommand utilizes the gbpcli
API and the [rich](https://pypi.org/project/rich/) library and is themable.
