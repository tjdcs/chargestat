class Chargestat < Formula
  include Language::Python::Virtualenv

  desc "Mac power adapter, charge rate, and time-to-full/empty in the terminal"
  homepage "https://github.com/tjdcs/chargestat"
  url "https://github.com/tjdcs/chargestat/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "REPLACE_WITH_SHA256"
  license "MIT"

  depends_on :macos
  depends_on "python@3.14"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/chargestat --version")
  end
end
