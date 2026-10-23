# README demo. Re-record on a MacBook with: vhs docs/demo.tape
# Runs the real chargestat on PATH, so the numbers are live.

Output docs/demo.gif

Set Shell "bash"
Set FontFamily "BlexMono Nerd Font Mono"
Set FontSize 18
Set Width 1240
Set Height 680
Set Padding 24
Set Margin 24
Set MarginFill "#3b4252"
Set WindowBar Colorful
Set BorderRadius 10
# Tucker's iTerm2 Default profile (all sRGB), with the tab color as the margin.
Set Theme { "name": "iTerm2 Default", "background": "#212121", "foreground": "#f8f8f2", "selection": "#f8f8f2", "cursor": "#eceff4", "black": "#21222c", "brightBlack": "#545454", "red": "#ff5555", "brightRed": "#ff6e6e", "green": "#50fa7b", "brightGreen": "#69ff94", "yellow": "#ffcb6b", "brightYellow": "#ffcb6b", "blue": "#82aaff", "brightBlue": "#d6acff", "magenta": "#c792ea", "brightMagenta": "#ff92df", "cyan": "#8be9fd", "brightCyan": "#a4ffff", "white": "#f8f8f2", "brightWhite": "#f8f8f2" }
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
