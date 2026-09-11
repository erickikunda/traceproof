package repository

import "os/exec"

func Execute(value string) {
	exec.Command("sh", "-c", "printf safe").Run()
}
