/* Promedio de dos enteros sin desborde: (a + b) / 2 desborda con a = b = INT_MAX. */

/*@ requires 0 <= a <= b;
    assigns \nothing;
    ensures \result == (a + b) / 2;
*/
int promedio(int a, int b)
{
    return a + (b - a) / 2;
}
