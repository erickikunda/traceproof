package main
import "net/http"
import "os/exec"
func handler(w http.ResponseWriter, r *http.Request) {
 value := r.FormValue("command")
 exec.Command("printf", "%s", value).Run()
}
func main() { http.HandleFunc("/run", handler) }
