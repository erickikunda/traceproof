#include <stdlib.h>
int main(int count, char *inputs[]) {
 if (count > 1) {
  const char *command = inputs[1];
  return system(command);
 }
 return 0;
}
