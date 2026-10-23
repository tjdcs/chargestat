# README demo. Re-record on a MacBook with: vhs docs/demo.tape
# Runs the real chargestat on PATH, so the numbers are live.

Output docs/demo.gif

Set Shell "bash"
Set FontSize 18
Set Width 1240
Set Height 680
Set Padding 24
Set Margin 24
Set MarginFill "#6c7086"
Set WindowBar Colorful
Set BorderRadius 10
Set Theme "Catppuccin Mocha"
Set TypingSpeed 70ms

Env BASH_SILENCE_DEPRECATION_WARNING "1"

Hide
Type "export PATH=/opt/homebrew/bin:$PATH PS1='\[\e[1;35m\]❯\[\e[0m\] '; clear"
Enter
Show

Sleep 600ms
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
