package main

import "os/exec"

func lookup(input string) {
	exec.Command("sh", "-c", input).Run()
}

func main() {}
