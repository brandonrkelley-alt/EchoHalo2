import com.pocketstudio.app.core.EditDiagnostics;

public final class EditDiagnosticsTests {
    public static void main(String[] args) {
        int[] a={0xff000000,0xffffffff,0xff808080,0xff00ff00};
        int[] b=a.clone();
        assertNear(0,EditDiagnostics.meanRgbDelta(a,b),1e-10,"identical result");
        b[1]=0xff000000;
        if(EditDiagnostics.meanRgbDelta(a,b)<10)throw new AssertionError("Large image difference was missed");
        assertNear(100,EditDiagnostics.maskCoveragePercent(null),1e-10,"no mask");
        assertNear(50,EditDiagnostics.maskCoveragePercent(new int[]{255,0,255,0}),1e-10,"half mask");
        try{EditDiagnostics.meanRgbDelta(a,new int[2]);throw new AssertionError("Mismatched arrays accepted");}
        catch(IllegalArgumentException expected){}
        System.out.println("EditDiagnosticsTests: 5 checks passed.");
    }
    private static void assertNear(double expected,double actual,double eps,String name){
        if(Math.abs(expected-actual)>eps)throw new AssertionError(name+": expected "+expected+" got "+actual);
    }
}
