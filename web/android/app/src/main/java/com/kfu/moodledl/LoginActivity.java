package com.kfu.moodledl;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.appcompat.app.AppCompatActivity;
import android.widget.TextView;

public class LoginActivity extends AppCompatActivity {

    public static final String EXTRA_SERVER = "server";
    private String server;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        server = getIntent().getStringExtra(EXTRA_SERVER);
        if (server == null || server.isEmpty()) {
            server = "https://elearning.kfu.edu.eg";
        }

        try {
            CookieManager.getInstance().setAcceptCookie(true);
        } catch (Exception ignored) {
        }

        WebView web = new WebView(this);
        web.setLayoutParams(new android.view.ViewGroup.LayoutParams(
            android.view.ViewGroup.LayoutParams.MATCH_PARENT,
            android.view.ViewGroup.LayoutParams.MATCH_PARENT));

        try {
            WebSettings s = web.getSettings();
            s.setJavaScriptEnabled(true);
            s.setDomStorageEnabled(true);
            s.setLoadWithOverviewMode(true);
            s.setUseWideViewPort(true);
            s.setCacheMode(WebSettings.LOAD_DEFAULT);
            s.setSupportZoom(true);
            s.setBuiltInZoomControls(true);
            s.setDisplayZoomControls(false);
        } catch (Exception ignored) {
        }

        try {
            web.setWebViewClient(new WebViewClient() {
                @Override
                public void onPageFinished(WebView view, String url) {
                    try {
                        if (tryCaptureToken()) {
                            // done, result already set via setResult/finish
                        }
                    } catch (Throwable ignored) {
                    }
                }
            });
        } catch (Throwable ignored) {
        }

        setContentView(web);

        try {
            web.loadUrl(server + "/login/index.php");
        } catch (Throwable t) {
            finishWithError(t);
        }
    }

    private boolean tryCaptureToken() {
        String cookie = null;
        try {
            cookie = CookieManager.getInstance().getCookie(server);
        } catch (Throwable ignored) {
        }
        if (cookie == null || !cookie.contains("MoodleSession")) {
            return false;
        }
        String session = null;
        String full = "";
        for (String part : cookie.split(";")) {
            String t = part.trim();
            if (!full.isEmpty()) full += "; ";
            full += t;
            if (t.startsWith("MoodleSession")) {
                int idx = t.indexOf('=');
                if (idx >= 0) session = t.substring(idx + 1).trim();
            }
        }
        if (session == null || session.isEmpty()) {
            return false;
        }
        Intent data = new Intent();
        data.putExtra("token", session);
        data.putExtra("cookie", full);
        setResult(RESULT_OK, data);
        try { finish(); } catch (Throwable ignored) {}
        return true;
    }

    private void finishWithError(Throwable t) {
        try {
            TextView tv = new TextView(this);
            tv.setText("Login error: " + (t != null ? t.getMessage() : "unknown"));
            setContentView(tv);
        } catch (Throwable ignored) {
            try { setResult(RESULT_CANCELED); finish(); } catch (Throwable ignored2) {}
        }
    }

    @Override
    public void onBackPressed() {
        setResult(RESULT_CANCELED);
        finish();
    }
}