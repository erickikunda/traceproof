package main
import "net/http"
import "os/exec"
func handler(w http.ResponseWriter, r *http.Request) {
 _ = r.FormValue("command")
 exec.Command("sh", "-c", "echo fixed").Run()
}
func main() { http.HandleFunc("/run", handler) }
