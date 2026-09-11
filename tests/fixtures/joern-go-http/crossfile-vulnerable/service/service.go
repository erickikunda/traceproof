package service
import "example.com/probe/repository"
func Dispatch(value string) { repository.Execute(value) }
