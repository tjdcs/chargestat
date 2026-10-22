# Releasing

Pushing a `vX.Y.Z` tag runs `.github/workflows/release.yml`, which builds the sdist and wheel, publishes them to PyPI, and creates a GitHub release. The Homebrew tap is then updated by hand with `packaging/homebrew/bump.sh`.

## One-time setup

1. **Make the repository public.** Homebrew downloads the tag tarball without credentials.
   ```sh
   gh repo edit tjdcs/chargestat --visibility public --accept-visibility-change-consequences
   ```
2. **PyPI trusted publisher.** On pypi.org → Your projects → Publishing → *Add a new pending publisher*: project `chargestat`, owner `tjdcs`, repository `chargestat`, workflow `release.yml`, environment `pypi`. No API token is needed.
3. **GitHub environment.** Repo Settings → Environments → create `pypi` (optionally require approval).
4. **Tap repository.** Homebrew maps `tjdcs/tap` to `github.com/tjdcs/homebrew-tap`:
   ```sh
   gh repo create tjdcs/homebrew-tap --public --add-readme --description "Homebrew formulae"
   brew tap tjdcs/tap   # clone lives at $(brew --repo tjdcs/tap)
   ```

## Each release

```sh
uv version --bump patch            # or minor / major; edits pyproject.toml
uv lock
git commit -am "Release v$(uv version --short)"
git tag "v$(uv version --short)"
git push && git push --tags        # triggers PyPI + GitHub release
```

Then update the tap once the tag tarball exists:

```sh
v=$(uv version --short)
packaging/homebrew/bump.sh "$v"    # writes into $(brew --repo tjdcs/tap)
brew install --build-from-source tjdcs/tap/chargestat && brew test tjdcs/tap/chargestat
brew audit --strict --online tjdcs/tap/chargestat
git -C "$(brew --repo tjdcs/tap)" add Formula/chargestat.rb
git -C "$(brew --repo tjdcs/tap)" commit -m "chargestat $v" && git -C "$(brew --repo tjdcs/tap)" push
```

## Notes

- The build backend is `flit_core` on purpose. Homebrew's `virtualenv_install_with_resources` builds from source with `--no-binary :all:`, so `uv_build` (Rust) fails without a toolchain; `flit_core` is pure Python and dependency-free.
- The package has no runtime dependencies, so the formula needs no `resource` blocks. If you add a dependency, run `brew update-python-resources chargestat` in the tap.
- Verify `uvx` from PyPI after release: `uvx --refresh chargestat -V`.
