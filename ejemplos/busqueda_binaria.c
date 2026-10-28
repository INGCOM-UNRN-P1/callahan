/* Búsqueda binaria sobre un arreglo ordenado.
   El punto medio se calcula como inicio + (fin - inicio) / 2: con (inicio + fin) / 2
   la suma desborda para arreglos grandes y -wp-rte no lo puede demostrar. */

/*@ predicate ordenado(int *v, integer n) =
      \forall integer i, j; 0 <= i <= j < n ==> v[i] <= v[j];
*/

/*@ requires n >= 0;
    requires \valid_read(v + (0 .. n - 1));
    requires ordenado(v, n);
    assigns \nothing;
    behavior encontrado:
      assumes \exists integer k; 0 <= k < n && v[k] == x;
      ensures 0 <= \result < n && v[\result] == x;
    behavior ausente:
      assumes \forall integer k; 0 <= k < n ==> v[k] != x;
      ensures \result == -1;
    complete behaviors;
    disjoint behaviors;
*/
int buscar_binaria(const int *v, int n, int x)
{
    int inicio = 0;
    int fin = n - 1;
    /*@ loop invariant 0 <= inicio <= n;
        loop invariant -1 <= fin < n;
        loop invariant \forall integer k; 0 <= k < inicio ==> v[k] < x;
        loop invariant \forall integer k; fin < k < n ==> v[k] > x;
        loop assigns inicio, fin;
        loop variant fin - inicio;
    */
    while (inicio <= fin) {
        int medio = inicio + (fin - inicio) / 2;
        if (v[medio] < x) {
            inicio = medio + 1;
        } else if (v[medio] > x) {
            fin = medio - 1;
        } else {
            return medio;
        }
    }
    return -1;
}
