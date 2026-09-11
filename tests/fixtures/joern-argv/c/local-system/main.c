int system(const char *text) { return 0; }
int main(int count, char **arguments) {
 if (count > 1) {
  const char *command = arguments[1];
  return system(command);
 }
 return 0;
}
