package com.kfu.moodledl;

import android.content.Intent;
import androidx.activity.result.ActivityResult;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "MoodleLogin")
public class MoodleLoginPlugin extends Plugin {

    @PluginMethod
    public void login(PluginCall call) {
        String server = call.getString("server", "https://elearning.kfu.edu.eg");
        Intent intent = new Intent(getActivity(), LoginActivity.class);
        intent.putExtra(LoginActivity.EXTRA_SERVER, server);
        startActivityForResult(call, intent, "loginResult");
    }

    @ActivityCallback
    private void loginResult(PluginCall call, ActivityResult result) {
        if (call == null) {
            return;
        }
        if (result == null || result.getData() == null) {
            call.reject("Login cancelled");
            return;
        }
        Intent data = result.getData();
        String token = data.getStringExtra("token");
        String cookie = data.getStringExtra("cookie");
        if (token == null || token.isEmpty()) {
            call.reject("Login failed: no session token captured");
            return;
        }
        JSObject ret = new JSObject();
        ret.put("token", token);
        ret.put("cookie", cookie);
        call.resolve(ret);
    }
}