# running the tests

First allow git, to access the `file://` protocol:

```
git config --global protocol.file.allow always
```

Then run the tests with `make test`

Do not forget to undo the global setting:

```
git config --global protocol.file.allow never
```
