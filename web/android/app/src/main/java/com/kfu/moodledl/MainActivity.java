package com.kfu.moodledl;

import android.os.Bundle;
import android.util.Log;
import java.io.FileOutputStream;
import android.widget.Toast;

import com.getcapacitor.BridgeActivity;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler() {
            @Override
            public void uncaughtException(Thread thread, Throwable throwable) {
                try {
                    File dir = getExternalFilesDir(null);
                    if (dir != null) {
                        File f = new File(dir, "crash.txt");
                        PrintWriter pw = new PrintWriter(new FileOutputStream(f, true));
                        pw.println("=== " + new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date()) + " ===");
                        throwable.printStackTrace(pw);
                        pw.close();
                    }
                } catch (Throwable ignored) {
                }
                Log.e("KFUCRASH", Log.getStackTraceString(throwable));
                try {
                    Toast.makeText(getApplicationContext(), "Error: " + throwable, Toast.LENGTH_LONG).show();
                } catch (Throwable ignored) {
                }
                android.os.Process.killProcess(android.os.Process.myPid());
            }
        });

        registerPlugin(MoodleLoginPlugin.class);
        super.onCreate(savedInstanceState);
    }
}