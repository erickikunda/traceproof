package main
import "net/http"
import exec "example.com/otherexec"
func handler(w http.ResponseWriter, r *http.Request) {
 value := r.FormValue("command")
 exec.Command("sh", "-c", value).Run()
}
func main() { http.HandleFunc("/run", handler) }
