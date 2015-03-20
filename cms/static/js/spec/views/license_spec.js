define(["js/views/license", "js/models/license", "js/common_helpers/template_helpers"],
       function(LicenseView, LicenseModel, TemplateHelpers) {
  describe("License view", function() {

    beforeEach(function() {
      TemplateHelpers.installTemplate("license-selector", true);
      this.model = new LicenseModel();
      this.view = new LicenseView({model: this.model});
    })

    it("renders with no license", function() {
      this.view.render();
      expect(this.view.$("li[data-license=all-rights-reserved] button"))
        .toHaveText("All Rights Reserved");
      expect(this.view.$("li[data-license=all-rights-reserved] button"))
        .not.toHaveClass("is-selected");
      expect(this.view.$("li[data-license=creative-commons] button"))
        .toHaveText("Creative Commons");
      expect(this.view.$("li[data-license=creative-commons] button"))
        .not.toHaveClass("is-selected");
    });

    it("renders with the right license selected", function() {
      this.model.set("type", "all-rights-reserved");
      expect(this.view.$("li[data-license=all-rights-reserved] button"))
        .toHaveClass("is-selected");
      expect(this.view.$("li[data-license=creative-commons] button"))
        .not.toHaveClass("is-selected");
    });

  })
})
