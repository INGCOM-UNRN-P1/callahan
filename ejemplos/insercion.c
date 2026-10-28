/* Ordenamiento por inserción: al terminar, el arreglo queda ordenado. */

/*@ predicate ordenado(int *v, integer desde, integer hasta) =
      \forall integer i, j; desde <= i <= j < hasta ==> v[i] <= v[j];
*/

/*@ requires n >= 0;
    requires \valid(v + (0 .. n - 1));
    assigns v[0 .. n - 1];
    ensures ordenado(v, 0, n);
*/
void ordenar_insercion(int *v, int n)
{
    /*@ loop invariant 0 <= i <= n;
        loop invariant i > 0 ==> ordenado(v, 0, i);
        loop assigns i, v[0 .. n - 1];
        loop variant n - i;
    */
    for (int i = 0; i < n; i++) {
        int actual = v[i];
        int j = i;
        /*@ loop invariant 0 <= j <= i;
            loop invariant ordenado(v, 0, j);
            loop invariant ordenado(v, j + 1, i + 1);
            loop invariant \forall integer k; j < k <= i ==> v[k] > actual;
            loop invariant 0 < j < i ==> v[j - 1] <= v[j + 1];
            loop assigns j, v[0 .. i];
            loop variant j;
        */
        while (j > 0 && v[j - 1] > actual) {
            v[j] = v[j - 1];
            j--;
        }
        v[j] = actual;
    }
}
