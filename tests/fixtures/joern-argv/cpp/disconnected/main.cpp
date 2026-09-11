#include <stdlib.h>
int main(int count, char **arguments) {
 if (count > 1) {
  const char *command = arguments[1];
  return 0;
 }
 return 0;
}

int unrelated(const char *value) { return system(value); }
