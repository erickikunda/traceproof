package main

import "os/exec"

func lookup(input string) {
	exec.Command("sh", "-c", "printf safe").Run()
}

func main() {}
