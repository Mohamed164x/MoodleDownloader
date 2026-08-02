package com.kfu.moodledl;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

public class LoginActivity extends AppCompatActivity {

    public static final String EXTRA_SERVER = "server";

    private String server;
    private WebView web;
    private TextView errorView;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable poll = new Runnable() {
        @Override
        public void run() {
            if (!isFinishing() && !isDestroyed()) {
                try {
                    if (tryCaptureToken()) {
                        return;
                    }
                } catch (Throwable t) {
                    showError("Poll error: " + dump(t));
                }
            }
            handler.postDelayed(this, 700);
        }
    };

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            buildUi();
        } catch (Throwable t) {
            showError("onCreate failed: " + dump(t));
            return;
        }
        try {
            String url = server + "/login/index.php";
            web.loadUrl(url);
        } catch (Throwable t) {
            showError("loadUrl failed: " + dump(t));
        }
    }

    private void buildUi() {
        server = getIntent().getStringExtra(EXTRA_SERVER);
        if (server == null || server.isEmpty()) {
            server = "https://elearning.kfu.edu.eg";
        }
        if (!server.startsWith("http://") && !server.startsWith("https://")) {
            server = "https://" + server;
        }
        serverUrl = server;

        try {
            CookieManager.getInstance().setAcceptCookie(true);
        } catch (Throwable ignored) {
        }

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#0f172a"));

        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(16, 12, 16, 12);
        bar.setBackgroundColor(Color.parseColor("#1e293b"));

        TextView title = new TextView(this);
        title.setText("Log in to Moodle");
        title.setTextColor(Color.WHITE);
        title.setTextSize(16);
        title.setLayoutParams(new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        bar.addView(title);

        Button close = new Button(this);
        close.setText("Done");
        close.setAllCaps(false);
        close.setOnClickListener(v -> {
            setResult(RESULT_CANCELED);
            finish();
        });
        bar.addView(close);

        root.addView(bar, new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        errorView = new TextView(this);
        errorView.setTextColor(Color.rgb(255, 100, 100));
        errorView.setTextSize(13);
        errorView.setPadding(16, 12, 16, 12);
        errorView.setVisibility(TextView.GONE);
        root.addView(errorView, new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        web = new WebView(this);
        WebSettings s = web.getSettings();
        try {
            s.setJavaScriptEnabled(true);
            s.setDomStorageEnabled(true);
            s.setLoadWithOverviewMode(true);
            s.setUseWideViewPort(true);
            s.setCacheMode(WebSettings.LOAD_DEFAULT);
            s.setSupportZoom(true);
            s.setBuiltInZoomControls(true);
            s.setDisplayZoomControls(false);
        } catch (Throwable ignored) {
        }

        try {
            web.setWebViewClient(new WebViewClient() {
                @Override
                public void onPageFinished(WebView view, String url) {
                    try {
                        tryCaptureToken();
                    } catch (Throwable t) {
                        showError("onPageFinished: " + dump(t));
                    }
                }
            });
        } catch (Throwable ignored) {
        }

        root.addView(web, new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        setContentView(scroll);

        handler.postDelayed(poll, 800);
    }

    private String serverUrl;

    private boolean tryCaptureToken() {
        String cookie = null;
        try {
            cookie = CookieManager.getInstance().getCookie(serverUrl);
        } catch (Throwable ignored) {
        }
        if (cookie == null || !cookie.contains("MoodleSession")) {
            String host = serverUrl.replaceFirst("^(https?://)?(www\\.)?", "").replaceFirst("/.*$", "");
            try {
                String c2 = CookieManager.getInstance().getCookie(host);
                if (c2 != null && c2.contains("MoodleSession")) cookie = c2;
            } catch (Throwable ignored2) {
            }
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
        handler.removeCallbacks(poll);
        try { finish(); } catch (Throwable ignored) {
        }
        return true;
    }

    private void showError(String msg) {
        handler.post(() -> {
            try {
                if (errorView != null) {
                    errorView.setText(msg);
                    errorView.setVisibility(TextView.VISIBLE);
                }
            } catch (Throwable ignored) {
            }
        });
    }

    private static String dump(Throwable t) {
        StringBuilder sb = new StringBuilder();
        if (t != null) {
            sb.append(t.getClass().getName()).append(": ").append(t.getMessage()).append("\n");
            for (StackTraceElement e : t.getStackTrace()) {
                sb.append("  at ").append(e.getClassName()).append(".").append(e.getMethodName())
                  .append("(").append(e.getFileName()).append(":").append(e.getLineNumber()).append(")\n");
                if (sb.length() > 3000) break;
            }
        }
        return sb.toString();
    }

    @Override
    public void onBackPressed() {
        setResult(RESULT_CANCELED);
        finish();
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacks(poll);
        super.onDestroy();
    }
}