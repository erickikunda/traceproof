package main

import "os/exec"

func lookup(input string) string { return input }

func unrelated(value string) {
	exec.Command("sh", "-c", value).Run()
}

func main() {}
