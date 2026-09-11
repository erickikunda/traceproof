package service

import "example.com/traceproofprobe/repository"

func Run(value string) {
	repository.Execute(value)
}
