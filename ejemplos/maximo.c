/* Máximo de un arreglo: invariante de lazo, variante y acceso a memoria. */

/*@ requires n > 0;
    requires \valid_read(v + (0 .. n - 1));
    assigns \nothing;
    ensures \forall integer k; 0 <= k < n ==> v[k] <= \result;
    ensures \exists integer k; 0 <= k < n && v[k] == \result;
*/
int maximo(const int *v, int n)
{
    int max = v[0];
    /*@ loop invariant 1 <= i <= n;
        loop invariant \forall integer k; 0 <= k < i ==> v[k] <= max;
        loop invariant \exists integer k; 0 <= k < i && v[k] == max;
        loop assigns i, max;
        loop variant n - i;
    */
    for (int i = 1; i < n; i++) {
        if (v[i] > max) {
            max = v[i];
        }
    }
    return max;
}
