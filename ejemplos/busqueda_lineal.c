/* Búsqueda lineal: devuelve la primera posición de x o -1. */

/*@ requires n >= 0;
    requires \valid_read(v + (0 .. n - 1));
    assigns \nothing;
    behavior encontrado:
      assumes \exists integer k; 0 <= k < n && v[k] == x;
      ensures 0 <= \result < n && v[\result] == x;
      ensures \forall integer k; 0 <= k < \result ==> v[k] != x;
    behavior ausente:
      assumes \forall integer k; 0 <= k < n ==> v[k] != x;
      ensures \result == -1;
    complete behaviors;
    disjoint behaviors;
*/
int buscar(const int *v, int n, int x)
{
    /*@ loop invariant 0 <= i <= n;
        loop invariant \forall integer k; 0 <= k < i ==> v[k] != x;
        loop assigns i;
        loop variant n - i;
    */
    for (int i = 0; i < n; i++) {
        if (v[i] == x) {
            return i;
        }
    }
    return -1;
}
