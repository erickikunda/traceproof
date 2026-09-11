package main
import "net/http"
import "example.com/probe/service"
func handler(w http.ResponseWriter, r *http.Request) {
 value := r.FormValue("command")
 service.Dispatch(value)
}
func main() { http.HandleFunc("/run", handler) }
