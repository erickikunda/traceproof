package main
import "net/http"
import "os/exec"
func handler(w http.ResponseWriter, r *http.Request) {
 _ = r.FormValue("command")
}
func unrelated(value string) {
 exec.Command("sh", "-c", value).Run()
}
func main() { http.HandleFunc("/run", handler) }
