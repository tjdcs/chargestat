# uvx demo: a first run with an empty uv cache. Re-record with: vhs docs/uvx.tape

Output docs/uvx.gif

Set Height 680
Source docs/style.tape

Hide
Type "export PATH=/opt/homebrew/bin:$PATH UV_CACHE_DIR=$(mktemp -d) PS1='\[\e[1;35m\]❯\[\e[0m\] '; clear"
Enter
Show

Sleep 600ms
Type "uvx chargestat  # uv tmp install"
Sleep 400ms
Enter
# The download time varies, so wait for the output rather than a fixed sleep.
Wait+Screen@30s /battery gauge/
Sleep 5s

Ctrl+L
Sleep 300ms
Type "uvx chargestat -H"
Sleep 400ms
Enter
Wait+Screen@30s /powerlog samples/
Sleep 5s
