% ============================================================
% Monte-Carlo Simulation Framework
% MUSIC vs NLMS DoA Estimation
%
% Experiments:
% 1) RMSE and Pres vs SNR
% 2) RMSE and Pres vs Number of Snapshots (N)
% 3) RMSE and Pres vs NLMS Step Size (mu)
%
% Ahmed Yasser Hafez
% ============================================================

clear; clc; close all;

%% ============================================================
% GLOBAL PARAMETERS
% =============================================================

num_trials = 1000;          % Monte Carlo trials
L = 2;                     % Number of antennas
d = 0.5;                   % Inter-element spacing (lambda)
theta_true = 20;           % True DoA (degrees)

theta_scan = -90:1:90;     % Angular search grid
num_angles = length(theta_scan);

epsilon = 1e-6;            % NLMS regularization
threshold_deg = 2.0;       % Success if |error| <= threshold_deg

% Steering matrix for all scan angles
A_scan = exp(-1j * 2*pi*d*(0:L-1)' * sind(theta_scan));

%% ============================================================
% EXPERIMENT 1: RMSE and Pres vs SNR
% =============================================================

fprintf('\n========================================\n');
fprintf('Experiment 1: RMSE and Pres vs SNR\n');
fprintf('========================================\n');

snr_range = -15:5:20;

N_fixed = 100;
mu_fixed = 0.1;

rmse_music_snr = zeros(length(snr_range),1);
rmse_nlms_snr  = zeros(length(snr_range),1);
pres_music_snr = zeros(length(snr_range),1);
pres_nlms_snr   = zeros(length(snr_range),1);

for idx = 1:length(snr_range)

    SNR = snr_range(idx);

    err_music = zeros(num_trials,1);
    err_nlms  = zeros(num_trials,1);

    for trial = 1:num_trials

        % Generate source signal
        s = (randn(1,N_fixed) + 1j*randn(1,N_fixed))/sqrt(2);

        % True steering vector
        a_true = exp(-1j * 2*pi*d*(0:L-1)' * sind(theta_true));

        % Clean received signal
        X = a_true * s;

        % AWGN
        noise = (randn(L,N_fixed) + 1j*randn(L,N_fixed))/sqrt(2);

        signal_power = mean(abs(X(:)).^2);
        noise_power = signal_power / (10^(SNR/10));

        Xn = X + sqrt(noise_power) * noise;

        %% MUSIC
        R = (Xn * Xn') / N_fixed;

        [Evec, Eval] = eig(R);
        [~, sort_idx] = sort(diag(Eval), 'descend');
        Evec = Evec(:, sort_idx);

        En = Evec(:,2:end);

        denom = sum(abs(En' * A_scan).^2, 1);
        [~, idx_music] = min(denom);

        theta_est_music = theta_scan(idx_music);
        err_music(trial) = theta_est_music - theta_true;

        %% NLMS
        P_nlms = zeros(1, num_angles);

        for k = 1:num_angles
            w = zeros(L,1);
            a_k = A_scan(:,k);

            for n = 1:N_fixed
                x_n = Xn(:,n);
                d_des = a_k' * x_n;
                y = w' * x_n;
                e = d_des - y;

                w = w + mu_fixed * x_n * conj(e) / (norm(x_n)^2 + epsilon);
            end

            P_nlms(k) = norm(w)^2;
        end

        [~, idx_nlms] = max(P_nlms);
        theta_est_nlms = theta_scan(idx_nlms);
        err_nlms(trial) = theta_est_nlms - theta_true;
    end

    rmse_music_snr(idx) = sqrt(mean(err_music.^2));
    rmse_nlms_snr(idx)  = sqrt(mean(err_nlms.^2));

    pres_music_snr(idx) = sum(abs(err_music) <= threshold_deg) / num_trials;
    pres_nlms_snr(idx)   = sum(abs(err_nlms) <= threshold_deg) / num_trials;

    fprintf('SNR = %2d dB | MUSIC RMSE = %.2f | NLMS RMSE = %.2f | MUSIC Pres = %.2f | NLMS Pres = %.2f\n',...
        SNR, rmse_music_snr(idx), rmse_nlms_snr(idx), pres_music_snr(idx), pres_nlms_snr(idx));
end

%% Plot: RMSE vs SNR
figure;
plot(snr_range, rmse_music_snr, '-ob', 'LineWidth', 2); hold on;
plot(snr_range, rmse_nlms_snr,  '-sr', 'LineWidth', 2);
grid on;
xlabel('SNR (dB)');
ylabel('RMSE (degrees)');
title('RMSE vs SNR');
legend('MUSIC','NLMS','Location','northwest');

%% Plot: Pres vs SNR
figure;
plot(snr_range, pres_music_snr, '-ob', 'LineWidth', 2); hold on;
plot(snr_range, pres_nlms_snr,  '-sr', 'LineWidth', 2);
grid on;
xlabel('SNR (dB)');
ylabel('Probability of Resolution');
title(sprintf('Probability of Resolution vs SNR (Threshold = \\pm%.1f^\\circ)', threshold_deg));
legend('MUSIC','NLMS','Location','southeast');
ylim([0 1.05]);

%% ============================================================
% EXPERIMENT 2: RMSE and Pres vs Number of Snapshots
% =============================================================

fprintf('\n========================================\n');
fprintf('Experiment 2: RMSE and Pres vs Number of Snapshots\n');
fprintf('========================================\n');

N_range = [20 50 100 200 500];

SNR_fixed = 10;
mu_fixed = 0.1;

rmse_music_N = zeros(length(N_range),1);
rmse_nlms_N  = zeros(length(N_range),1);
pres_music_N = zeros(length(N_range),1);
pres_nlms_N  = zeros(length(N_range),1);

for idx = 1:length(N_range)

    N = N_range(idx);

    err_music = zeros(num_trials,1);
    err_nlms  = zeros(num_trials,1);

    for trial = 1:num_trials

        s = (randn(1,N) + 1j*randn(1,N))/sqrt(2);

        a_true = exp(-1j * 2*pi*d*(0:L-1)' * sind(theta_true));

        X = a_true * s;

        noise = (randn(L,N) + 1j*randn(L,N))/sqrt(2);

        signal_power = mean(abs(X(:)).^2);
        noise_power = signal_power / (10^(SNR_fixed/10));

        Xn = X + sqrt(noise_power) * noise;

        %% MUSIC
        R = (Xn * Xn') / N;

        [Evec, Eval] = eig(R);
        [~, sort_idx] = sort(diag(Eval), 'descend');
        Evec = Evec(:, sort_idx);

        En = Evec(:,2:end);

        denom = sum(abs(En' * A_scan).^2, 1);
        [~, idx_music] = min(denom);

        theta_est_music = theta_scan(idx_music);
        err_music(trial) = theta_est_music - theta_true;

        %% NLMS
        P_nlms = zeros(1, num_angles);

        for k = 1:num_angles
            w = zeros(L,1);
            a_k = A_scan(:,k);

            for n = 1:N
                x_n = Xn(:,n);
                d_des = a_k' * x_n;
                y = w' * x_n;
                e = d_des - y;

                w = w + mu_fixed * x_n * conj(e) / (norm(x_n)^2 + epsilon);
            end

            P_nlms(k) = norm(w)^2;
        end

        [~, idx_nlms] = max(P_nlms);
        theta_est_nlms = theta_scan(idx_nlms);
        err_nlms(trial) = theta_est_nlms - theta_true;
    end

    rmse_music_N(idx) = sqrt(mean(err_music.^2));
    rmse_nlms_N(idx)  = sqrt(mean(err_nlms.^2));

    pres_music_N(idx) = sum(abs(err_music) <= threshold_deg) / num_trials;
    pres_nlms_N(idx)   = sum(abs(err_nlms) <= threshold_deg) / num_trials;

    fprintf('N = %3d | MUSIC RMSE = %.2f | NLMS RMSE = %.2f | MUSIC Pres = %.2f | NLMS Pres = %.2f\n',...
        N, rmse_music_N(idx), rmse_nlms_N(idx), pres_music_N(idx), pres_nlms_N(idx));
end

%% Plot: RMSE vs Snapshots
figure;
plot(N_range, rmse_music_N, '-ob', 'LineWidth', 2); hold on;
plot(N_range, rmse_nlms_N,  '-sr', 'LineWidth', 2);
grid on;
xlabel('Number of Snapshots (N)');
ylabel('RMSE (degrees)');
title('RMSE vs Number of Snapshots');
legend('MUSIC','NLMS','Location','northeast');

%% Plot: Pres vs Snapshots
figure;
plot(N_range, pres_music_N, '-ob', 'LineWidth', 2); hold on;
plot(N_range, pres_nlms_N,  '-sr', 'LineWidth', 2);
grid on;
xlabel('Number of Snapshots (N)');
ylabel('Probability of Resolution');
title(sprintf('Probability of Resolution vs Snapshots (Threshold = \\pm%.1f^\\circ)', threshold_deg));
legend('MUSIC','NLMS','Location','southeast');
ylim([0 1.05]);

%% ============================================================
% EXPERIMENT 3: RMSE and Pres vs NLMS Step Size
% =============================================================

fprintf('\n========================================\n');
fprintf('Experiment 3: RMSE and Pres vs NLMS Step Size\n');
fprintf('========================================\n');

mu_range = [0.01 0.05 0.1 0.2 0.5];

SNR_fixed = 10;
N_fixed = 100;

rmse_nlms_mu = zeros(length(mu_range),1);
pres_nlms_mu = zeros(length(mu_range),1);

for idx = 1:length(mu_range)

    mu = mu_range(idx);

    err_nlms = zeros(num_trials,1);

    for trial = 1:num_trials

        s = (randn(1,N_fixed) + 1j*randn(1,N_fixed))/sqrt(2);

        a_true = exp(-1j * 2*pi*d*(0:L-1)' * sind(theta_true));

        X = a_true * s;

        noise = (randn(L,N_fixed) + 1j*randn(L,N_fixed))/sqrt(2);

        signal_power = mean(abs(X(:)).^2);
        noise_power = signal_power / (10^(SNR_fixed/10));

        Xn = X + sqrt(noise_power) * noise;

        %% NLMS
        P_nlms = zeros(1, num_angles);

        for k = 1:num_angles
            w = zeros(L,1);
            a_k = A_scan(:,k);

            for n = 1:N_fixed
                x_n = Xn(:,n);
                d_des = a_k' * x_n;
                y = w' * x_n;
                e = d_des - y;

                w = w + mu * x_n * conj(e) / (norm(x_n)^2 + epsilon);
            end

            P_nlms(k) = norm(w)^2;
        end

        [~, idx_nlms] = max(P_nlms);
        theta_est_nlms = theta_scan(idx_nlms);
        err_nlms(trial) = theta_est_nlms - theta_true;
    end

    rmse_nlms_mu(idx) = sqrt(mean(err_nlms.^2));
    pres_nlms_mu(idx) = sum(abs(err_nlms) <= threshold_deg) / num_trials;

    fprintf('mu = %.2f | NLMS RMSE = %.2f | NLMS Pres = %.2f\n',...
        mu, rmse_nlms_mu(idx), pres_nlms_mu(idx));
end

%% Plot: RMSE vs Step Size
figure;
plot(mu_range, rmse_nlms_mu, '-sr', 'LineWidth', 2);
grid on;
xlabel('NLMS Step Size (\mu)');
ylabel('RMSE (degrees)');
title('NLMS RMSE vs Step Size');
legend('NLMS','Location','northwest');

%% Plot: Pres vs Step Size
figure;
plot(mu_range, pres_nlms_mu, '-sr', 'LineWidth', 2);
grid on;
xlabel('NLMS Step Size (\mu)');
ylabel('Probability of Resolution');
title(sprintf('NLMS Probability of Resolution vs Step Size (Threshold = \\pm%.1f^\\circ)', threshold_deg));
legend('NLMS','Location','southeast');
ylim([0 1.05]);
