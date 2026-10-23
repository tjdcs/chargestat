# README demo. Re-record on a MacBook with: vhs docs/demo.tape
# Runs the real chargestat on PATH, so the numbers are live.

Output docs/demo.gif

Set Height 680
Source docs/style.tape

Hide
Type "export PATH=/opt/homebrew/bin:$PATH PS1='\[\e[1;35m\]❯\[\e[0m\] '; clear"
Enter
Show

Sleep 600ms
# A comment, so it shows without running brew; it stays above the snapshot.
Type "# brew install tjdcs/tap/chargestat"
Sleep 300ms
Enter
Sleep 1s
Type "chargestat"
Sleep 400ms
Enter
Sleep 5s

Ctrl+L
Sleep 300ms
Type "chargestat -H"
Sleep 400ms
Enter
Sleep 6s
